package com.niknolig.app

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.ProgressBar
import android.widget.Spinner
import android.widget.TextView
import org.elektroengel.core.AnalysisFailure
import org.elektroengel.core.AnalysisMode
import org.elektroengel.core.AnalysisOutcome
import org.elektroengel.core.AnalysisRequest
import org.elektroengel.core.ElectroEngelAnalyzer

class AssistantActivity : Activity() {
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
        val refinementInput = findViewById<EditText>(R.id.assistant_refinement_input)
        val modeInput = findViewById<Spinner>(R.id.assistant_analysis_mode)
        val requestStatus = findViewById<TextView>(R.id.assistant_request_status)
        val analyzeButton = findViewById<Button>(R.id.assistant_request_button)
        val refineButton = findViewById<Button>(R.id.assistant_refine_button)
        val progress = findViewById<ProgressBar>(R.id.assistant_analysis_progress)

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

    private fun failureMessage(failure: AnalysisFailure): String =
        when (failure) {
            AnalysisFailure.EMPTY_INPUT -> getString(R.string.assistant_analysis_empty)
            AnalysisFailure.INVALID_INPUT -> getString(R.string.assistant_analysis_error_invalid)
            AnalysisFailure.AI_DISABLED -> getString(R.string.assistant_analysis_error_ai_disabled)
            AnalysisFailure.TIMEOUT -> getString(R.string.assistant_analysis_error_timeout)
            AnalysisFailure.PROVIDER_UNAVAILABLE -> getString(R.string.assistant_analysis_error_unavailable)
        }
}
