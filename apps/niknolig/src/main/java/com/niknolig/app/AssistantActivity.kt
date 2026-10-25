package com.niknolig.app

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.Spinner
import android.widget.TextView
import java.util.UUID
import org.elektroengel.core.AnalysisFailure
import org.elektroengel.core.AnalysisMode
import org.elektroengel.core.AnalysisOutcome
import org.elektroengel.core.AnalysisRequest
import org.elektroengel.core.ElectroEngelAnalyzer

class AssistantActivity : Activity() {
    private val preferences by lazy {
        getSharedPreferences(ASSISTANT_PREFERENCES_FILE, MODE_PRIVATE)
    }
    private lateinit var refinementInput: EditText
    private lateinit var insertSummaryButton: Button
    private lateinit var taskInput: EditText
    private lateinit var taskStatus: TextView
    private lateinit var taskList: LinearLayout
    private var tasks = emptyList<AssistantTask>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_assistant)

        findViewById<Button>(R.id.assistant_close_button).setOnClickListener {
            finish()
        }

        findViewById<Button>(R.id.assistant_learning_profile_button).setOnClickListener {
            startActivity(Intent(this, LearningProfileActivity::class.java))
        }

        findViewById<Button>(R.id.assistant_support_button).setOnClickListener {
            startActivity(Intent(this, SupportActivity::class.java))
        }

        val requestInput = findViewById<EditText>(R.id.assistant_request_input)
        refinementInput = findViewById(R.id.assistant_refinement_input)
        val modeInput = findViewById<Spinner>(R.id.assistant_analysis_mode)
        val requestStatus = findViewById<TextView>(R.id.assistant_request_status)
        val analyzeButton = findViewById<Button>(R.id.assistant_request_button)
        val refineButton = findViewById<Button>(R.id.assistant_refine_button)
        val progress = findViewById<ProgressBar>(R.id.assistant_analysis_progress)
        insertSummaryButton = findViewById(R.id.assistant_insert_summary_button)
        insertSummaryButton.setOnClickListener { insertSavedSummary() }
        taskInput = findViewById(R.id.assistant_task_input)
        taskStatus = findViewById(R.id.assistant_task_status)
        taskList = findViewById(R.id.assistant_task_list)
        tasks = AssistantTaskStorage.decode(preferences.getString(KEY_TASKS, "").orEmpty())
        findViewById<Button>(R.id.assistant_task_add_button).setOnClickListener {
            addTask()
        }
        renderTasks()

        fun analyze() {
            val text = requestInput.text.toString()
            if (text.isBlank()) {
                requestStatus.text = getString(R.string.assistant_analysis_empty)
                return
            }

            val mode = AnalysisMode.values().getOrNull(modeInput.selectedItemPosition)
            if (mode == null) {
                requestStatus.text = getString(R.string.assistant_analysis_failed)
                return
            }
            val request = AnalysisRequest(
                mode = mode,
                text = text,
                refinement = refinementInput.text.toString(),
            )
            analyzeButton.isEnabled = false
            refineButton.isEnabled = false
            progress.visibility = ProgressBar.VISIBLE
            requestStatus.text = getString(R.string.assistant_analysis_loading)

            Thread({
                val outcome = runCatching { ElectroEngelAnalyzer.analyze(request) }
                    .getOrElse {
                        AnalysisOutcome.Failure(AnalysisFailure.PROVIDER_UNAVAILABLE)
                    }
                runOnUiThread {
                    if (isFinishing) return@runOnUiThread
                    progress.visibility = ProgressBar.GONE
                    analyzeButton.isEnabled = true
                    refineButton.isEnabled = true
                    requestStatus.text = when (outcome) {
                        is AnalysisOutcome.Success -> buildString {
                            outcome.result.sections.forEach { section ->
                                append(section.heading)
                                append("\n")
                                append(section.content)
                                append("\n\n")
                            }
                            append("Unsicherheit\n")
                            append(outcome.result.uncertainty)
                            append("\n\n")
                            append(getString(R.string.assistant_analysis_sources_unchecked))
                        }
                        is AnalysisOutcome.Failure -> failureMessage(outcome.reason)
                    }
                }
            }, "electro-engel-local-analysis").start()
        }
        analyzeButton.setOnClickListener { analyze() }
        refineButton.setOnClickListener { analyze() }
    }

    override fun onResume() {
        super.onResume()
        if (::insertSummaryButton.isInitialized) {
            insertSummaryButton.isEnabled = savedSummary().isNotEmpty()
        }
    }

    private fun savedSummary(): String =
        getSharedPreferences(LEARNING_PREFERENCES_FILE, MODE_PRIVATE)
            .getString(KEY_SESSION_SUMMARY, "")
            .orEmpty()
            .trim()

    private fun insertSavedSummary() {
        val summary = savedSummary()
        if (summary.isEmpty()) {
            insertSummaryButton.isEnabled = false
            return
        }
        val insert = {
            refinementInput.setText(summary)
            refinementInput.setSelection(summary.length)
        }
        if (refinementInput.text.isNullOrBlank()) {
            insert()
        } else {
            AlertDialog.Builder(this)
                .setMessage(R.string.assistant_summary_replace_confirmation)
                .setNegativeButton(android.R.string.cancel, null)
                .setPositiveButton(R.string.assistant_summary_replace_action) { _, _ -> insert() }
                .show()
        }
    }

    private fun addTask() {
        val title = AssistantTaskStorage.validTitle(taskInput.text.toString())
        if (title == null) {
            taskStatus.setText(R.string.assistant_task_invalid)
            return
        }
        if (tasks.size >= AssistantTaskStorage.MAX_TASKS) {
            taskStatus.setText(R.string.assistant_task_limit)
            return
        }
        tasks = tasks + AssistantTask(UUID.randomUUID().toString(), title)
        taskInput.text.clear()
        persistTasks()
    }

    private fun persistTasks() {
        preferences.edit().putString(KEY_TASKS, AssistantTaskStorage.encode(tasks)).apply()
        renderTasks()
    }

    private fun renderTasks() {
        if (!::taskList.isInitialized) return
        taskList.removeAllViews()
        if (tasks.isEmpty()) {
            taskStatus.setText(R.string.assistant_task_empty)
            return
        }
        taskStatus.text = getString(R.string.assistant_task_count, tasks.size)
        tasks.forEach { task ->
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = android.view.Gravity.CENTER_VERTICAL
            }
            val checkBox = CheckBox(this).apply {
                text = task.title
                isChecked = task.completed
                minHeight = resources.getDimensionPixelSize(R.dimen.touch_target)
                layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
                setOnCheckedChangeListener { _, checked ->
                    tasks = tasks.map {
                        if (it.id == task.id) it.copy(completed = checked) else it
                    }
                    persistTasks()
                }
            }
            val removeButton = Button(this).apply {
                setText(R.string.assistant_task_remove_button)
                setOnClickListener {
                    tasks = tasks.filterNot { it.id == task.id }
                    persistTasks()
                }
            }
            row.addView(checkBox)
            row.addView(removeButton)
            taskList.addView(row)
        }
    }

    private fun failureMessage(failure: AnalysisFailure): String =
        when (failure) {
            AnalysisFailure.EMPTY_INPUT -> getString(R.string.assistant_analysis_empty)
            AnalysisFailure.INVALID_INPUT -> getString(R.string.assistant_analysis_error_invalid)
            AnalysisFailure.AI_DISABLED -> getString(R.string.assistant_analysis_error_ai_disabled)
            AnalysisFailure.TIMEOUT -> getString(R.string.assistant_analysis_error_timeout)
            AnalysisFailure.PROVIDER_UNAVAILABLE -> getString(R.string.assistant_analysis_error_unavailable)
        }

    private companion object {
        const val ASSISTANT_PREFERENCES_FILE = "electro_angel_assistant"
        const val LEARNING_PREFERENCES_FILE = "electro_angel_learning"
        const val KEY_TASKS = "assistant_tasks"
        const val KEY_SESSION_SUMMARY = "session_summary"
    }
}
