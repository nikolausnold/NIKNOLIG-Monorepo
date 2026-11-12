package org.niknolig.devicelink

/** Minimal strict JSON codec for the small, bounded backend payloads. Numbers decode to Long/Double. */
object Json {
    fun encode(value: Any?): String = StringBuilder().also { write(it, value) }.toString()

    @Suppress("UNCHECKED_CAST")
    fun decodeObject(text: String): Map<String, Any?> =
        Parser(text).parseDocument() as? Map<String, Any?> ?: throw IllegalArgumentException("Not a JSON object")

    private fun write(out: StringBuilder, value: Any?) {
        when (value) {
            null -> out.append("null")
            is Boolean, is Int, is Long -> out.append(value.toString())
            is String -> writeString(out, value)
            is Map<*, *> -> {
                out.append('{')
                var first = true
                for ((key, item) in value) {
                    if (!first) out.append(',')
                    first = false
                    writeString(out, key as String)
                    out.append(':')
                    write(out, item)
                }
                out.append('}')
            }
            else -> throw IllegalArgumentException("Unsupported JSON value")
        }
    }

    private fun writeString(out: StringBuilder, text: String) {
        out.append('"')
        for (ch in text) {
            when {
                ch == '"' -> out.append("\\\"")
                ch == '\\' -> out.append("\\\\")
                ch < ' ' -> out.append("\\u").append(ch.code.toString(16).padStart(4, '0'))
                else -> out.append(ch)
            }
        }
        out.append('"')
    }

    private class Parser(private val text: String) {
        private var pos = 0

        fun parseDocument(): Any? {
            skip()
            val value = parseValue(0)
            skip()
            require(pos == text.length) { "Trailing data" }
            return value
        }

        private fun parseValue(depth: Int): Any? {
            require(depth <= MAX_DEPTH) { "Too deeply nested" }
            require(pos < text.length) { "Unexpected end" }
            return when (val ch = text[pos]) {
                '{' -> parseObject(depth)
                '[' -> parseArray(depth)
                '"' -> parseString()
                't' -> literal("true", true)
                'f' -> literal("false", false)
                'n' -> literal("null", null)
                else -> if (ch == '-' || ch in '0'..'9') parseNumber() else throw IllegalArgumentException("Bad JSON")
            }
        }

        private fun literal(word: String, value: Any?): Any? {
            require(text.startsWith(word, pos)) { "Bad literal" }
            pos += word.length
            return value
        }

        private fun parseObject(depth: Int): Map<String, Any?> {
            pos++
            val result = LinkedHashMap<String, Any?>()
            skip()
            if (peek() == '}') { pos++; return result }
            while (true) {
                skip()
                val key = parseString()
                skip()
                expect(':')
                skip()
                result[key] = parseValue(depth + 1)
                skip()
                when (next()) {
                    ',' -> continue
                    '}' -> return result
                    else -> throw IllegalArgumentException("Bad object")
                }
            }
        }

        private fun parseArray(depth: Int): List<Any?> {
            pos++
            val result = ArrayList<Any?>()
            skip()
            if (peek() == ']') { pos++; return result }
            while (true) {
                skip()
                result.add(parseValue(depth + 1))
                skip()
                when (next()) {
                    ',' -> continue
                    ']' -> return result
                    else -> throw IllegalArgumentException("Bad array")
                }
            }
        }

        private fun parseString(): String {
            expect('"')
            val out = StringBuilder()
            while (true) {
                require(pos < text.length) { "Unterminated string" }
                val ch = text[pos++]
                when {
                    ch == '"' -> return out.toString()
                    ch == '\\' -> {
                        require(pos < text.length) { "Bad escape" }
                        when (val esc = text[pos++]) {
                            '"', '\\', '/' -> out.append(esc)
                            'b' -> out.append('\b')
                            'f' -> out.append('\u000C')
                            'n' -> out.append('\n')
                            'r' -> out.append('\r')
                            't' -> out.append('\t')
                            'u' -> {
                                require(pos + 4 <= text.length) { "Bad unicode escape" }
                                out.append(text.substring(pos, pos + 4).toInt(16).toChar())
                                pos += 4
                            }
                            else -> throw IllegalArgumentException("Bad escape")
                        }
                    }
                    ch < ' ' -> throw IllegalArgumentException("Control character in string")
                    else -> out.append(ch)
                }
            }
        }

        private fun parseNumber(): Any {
            val start = pos
            if (peek() == '-') pos++
            while (pos < text.length && (text[pos] in '0'..'9' || text[pos] in ".eE+-")) pos++
            val token = text.substring(start, pos)
            return token.toLongOrNull() ?: token.toDouble()
        }

        private fun skip() {
            while (pos < text.length && text[pos] in " \t\n\r") pos++
        }

        private fun peek(): Char? = if (pos < text.length) text[pos] else null

        private fun next(): Char {
            require(pos < text.length) { "Unexpected end" }
            return text[pos++]
        }

        private fun expect(ch: Char) {
            require(next() == ch) { "Expected $ch" }
        }

        private companion object {
            const val MAX_DEPTH = 8
        }
    }
}
