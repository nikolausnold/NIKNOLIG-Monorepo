package com.niknolig.app

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.SharedPreferences
import android.os.Bundle
import android.text.InputFilter
import android.view.Gravity
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView

internal class SharedPreferencesText(
    private val preferences: SharedPreferences,
    private val key: String,
) : TextPersistence {
    private val persistence = RestoringTextPersistence(
        readValue = { preferences.getString(key, null) },
        writeValue = { preferences.edit().putString(key, it).commit() },
        restoreValue = { value ->
            val editor = preferences.edit()
            if (value == null) editor.remove(key) else editor.putString(key, value)
            editor.commit()
        },
        lock = preferences,
    )

    override fun read(): String? = persistence.read()
    override fun write(value: String): Boolean = persistence.write(value)
}

internal fun Context.localTaskRepository() = LocalTaskRepository(
    SharedPreferencesText(getSharedPreferences("local_tasks", Context.MODE_PRIVATE), "tasks"),
)

class TasksActivity : Activity() {
    private val repository by lazy { localTaskRepository() }
    private lateinit var input: EditText
    private lateinit var status: TextView
    private lateinit var list: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_tasks)
        input = findViewById(R.id.task_input)
        status = findViewById(R.id.task_status)
        list = findViewById(R.id.task_list)

        findViewById<Button>(R.id.task_add_button).setOnClickListener { addTask() }
        input.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_DONE) addTask()
            actionId == EditorInfo.IME_ACTION_DONE
        }
        findViewById<Button>(R.id.tasks_close_button).setOnClickListener { finish() }
        render(repository.list())
    }

    private fun addTask() {
        when (val result = repository.add(input.text.toString())) {
            is TaskResult.Success -> {
                input.text.clear()
                render(result.tasks, getString(R.string.task_saved))
            }
            is TaskResult.Failure -> showError(result.error)
        }
    }

    private fun handle(result: TaskResult, message: Int) {
        when (result) {
            is TaskResult.Success -> render(result.tasks, getString(message))
            is TaskResult.Failure -> {
                showError(result.error)
                render(repository.list(), status.text.toString())
            }
        }
    }

    private fun showError(error: TaskError) {
        status.text = getString(
            when (error) {
                TaskError.EMPTY, TaskError.TOO_LONG, TaskError.INVALID_CHARACTERS -> R.string.assistant_task_invalid
                TaskError.LIMIT_REACHED -> R.string.assistant_task_limit
                TaskError.NOT_FOUND -> R.string.task_not_found
                TaskError.STORAGE_FAILED -> R.string.task_storage_failed
            },
        )
    }

    private fun render(tasks: List<LocalTask>, message: String? = null) {
        status.text = message ?: if (tasks.isEmpty()) getString(R.string.assistant_task_empty)
        else getString(R.string.assistant_task_count, tasks.size)
        list.removeAllViews()
        tasks.sortedBy { it.done }.forEach { list.addView(row(it)) }
    }

    private fun row(task: LocalTask): View {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundResource(R.drawable.card_surface)
            val pad = resources.getDimensionPixelSize(R.dimen.space_medium)
            setPadding(pad, pad, pad, pad)
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT,
            ).apply { topMargin = resources.getDimensionPixelSize(R.dimen.space_small) }
        }
        row.addView(CheckBox(this).apply {
            text = task.title
            isChecked = task.done
            minHeight = resources.getDimensionPixelSize(R.dimen.touch_target)
            setTextColor(getColor(if (task.done) R.color.text_secondary else R.color.text_primary))
            if (task.done) paintFlags = paintFlags or android.graphics.Paint.STRIKE_THRU_TEXT_FLAG
            contentDescription = getString(R.string.task_done_description, task.title)
            setOnCheckedChangeListener { _, checked ->
                handle(repository.setDone(task.id, checked), R.string.task_saved)
            }
        })
        val actions = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.END
        }
        actions.addView(Button(this).apply {
            setText(R.string.task_edit_button)
            setOnClickListener { confirmEdit(task) }
        })
        actions.addView(Button(this).apply {
            setText(R.string.assistant_task_remove_button)
            setOnClickListener { confirmDelete(task) }
        })
        row.addView(actions)
        return row
    }

    private fun confirmEdit(task: LocalTask) {
        val editor = EditText(this).apply {
            setText(task.title)
            setSelection(text.length)
            filters = arrayOf(InputFilter.LengthFilter(LocalTaskRepository.MAX_TITLE_LENGTH))
            setSingleLine()
        }
        val dialog = AlertDialog.Builder(this)
            .setTitle(R.string.task_edit_title)
            .setView(editor)
            .setNegativeButton(android.R.string.cancel, null)
            .setPositiveButton(R.string.task_edit_save, null)
            .create()
        dialog.show()
        // Keep the dialog open on invalid input so the user can correct it.
        dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
            when (val result = repository.rename(task.id, editor.text.toString())) {
                is TaskResult.Success -> {
                    dialog.dismiss()
                    render(result.tasks, getString(R.string.task_saved))
                }
                is TaskResult.Failure -> editor.error = getString(
                    when (result.error) {
                        TaskError.STORAGE_FAILED -> R.string.task_storage_failed
                        TaskError.NOT_FOUND -> R.string.task_not_found
                        else -> R.string.assistant_task_invalid
                    },
                )
            }
        }
    }

    private fun confirmDelete(task: LocalTask) {
        AlertDialog.Builder(this)
            .setTitle(R.string.task_delete_title)
            .setMessage(getString(R.string.task_delete_message, task.title))
            .setNegativeButton(android.R.string.cancel, null)
            .setPositiveButton(R.string.task_delete_confirm) { _, _ ->
                handle(repository.delete(task.id), R.string.task_deleted)
            }
            .show()
    }
}
