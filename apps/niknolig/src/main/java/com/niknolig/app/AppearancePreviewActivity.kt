package com.niknolig.app

import android.app.Activity
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView

/** Local, static design samples; selections never represent live system state. */
class AppearancePreviewActivity : Activity() {
    private lateinit var situation: Spinner
    private lateinit var device: Spinner
    private lateinit var surface: Spinner
    private lateinit var host: LinearLayout
    private lateinit var card: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_appearance_preview)
        host = findViewById(R.id.preview_host)
        card = findViewById(R.id.preview_card)
        situation = selector(R.id.preview_situation, R.array.preview_situations, "situation", savedInstanceState)
        device = selector(R.id.preview_device, R.array.preview_devices, "device", savedInstanceState)
        surface = selector(R.id.preview_surface, R.array.preview_surfaces, "surface", savedInstanceState)
        val listener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                render()
            }
            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
        }
        listOf(situation, device, surface).forEach { it.onItemSelectedListener = listener }
        host.addOnLayoutChangeListener { _, left, _, right, _, oldLeft, _, oldRight, _ ->
            if (right - left != oldRight - oldLeft) render()
        }
        findViewById<Button>(R.id.preview_close).setOnClickListener { finish() }
        render()
    }

    private fun selector(id: Int, entries: Int, key: String, state: Bundle?): Spinner {
        val choices = resources.getStringArray(entries)
        return findViewById<Spinner>(id).apply {
            adapter = object : ArrayAdapter<String>(
                this@AppearancePreviewActivity, android.R.layout.simple_spinner_item, choices
            ) {
                override fun getView(position: Int, convertView: View?, parent: android.view.ViewGroup): View =
                    super.getView(position, convertView, parent).also {
                        (it as TextView).apply {
                            isSingleLine = false
                            setTextColor(getColor(R.color.text_primary))
                            setPadding(dp(8), dp(12), dp(8), dp(12))
                        }
                    }

                override fun getDropDownView(position: Int, convertView: View?, parent: android.view.ViewGroup): View =
                    super.getDropDownView(position, convertView, parent).also {
                        (it as TextView).apply {
                            isSingleLine = false
                            setTextColor(getColor(R.color.text_primary))
                            setBackgroundColor(getColor(R.color.dark_surface))
                            setPadding(dp(12), dp(16), dp(12), dp(16))
                        }
                    }
            }.apply { setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
            setSelection((state?.getInt(key) ?: 0).coerceIn(choices.indices))
        }
    }

    private fun render() {
        val state = situation.selectedItemPosition.coerceIn(0, 4)
        val tablet = device.selectedItemPosition == 1
        val website = surface.selectedItemPosition == 1
        val available = (host.width - host.paddingLeft - host.paddingRight).coerceAtLeast(0)
        // Target widths are bounded by the actual viewport, never an off-screen device canvas.
        val target = dp(if (tablet) 600 else 320)
        val padding = dp(if (website) 24 else 20)
        card.setPadding(padding, padding, padding, padding)
        if (available > 0) {
            card.layoutParams = (card.layoutParams as LinearLayout.LayoutParams).apply {
                width = minOf(available, target)
            }
        }
        card.background = GradientDrawable().apply {
            setColor(getColor(R.color.dark_surface))
            cornerRadius = resources.getDimension(R.dimen.preview_corner_radius)
            setStroke(dp(if (state >= 3) 3 else 1), getColor(R.color.brand_accent))
        }
        findViewById<ImageView>(R.id.preview_angel).apply {
            val contentWidth = (minOf(if (available > 0) available else target, target) - padding * 2).coerceAtLeast(0)
            val size = minOf(dp(if (tablet) 160 else 112), contentWidth)
            layoutParams = (layoutParams as LinearLayout.LayoutParams).apply {
                width = size
                height = size
            }
            rotation = floatArrayOf(0f, -4f, 4f, -8f, 8f)[state]
        }
        findViewById<TextView>(R.id.preview_sample_heading).apply {
            setText(if (website) R.string.preview_web_heading else R.string.preview_app_heading)
            textSize = (if (tablet) 24f else 20f) + (if (website) 2f else 0f)
        }
        findViewById<TextView>(R.id.preview_sample_body).setText(
            if (website) R.string.preview_web_body else R.string.preview_app_body
        )
        findViewById<TextView>(R.id.preview_status).text =
            resources.getStringArray(R.array.preview_states)[state]
        findViewById<TextView>(R.id.preview_status_detail).text =
            resources.getStringArray(R.array.preview_details)[state]
        findViewById<TextView>(R.id.preview_target_description).text = getString(
            R.string.preview_target_description, device.selectedItem, surface.selectedItem
        )
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putInt("situation", situation.selectedItemPosition)
        outState.putInt("device", device.selectedItemPosition)
        outState.putInt("surface", surface.selectedItemPosition)
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
