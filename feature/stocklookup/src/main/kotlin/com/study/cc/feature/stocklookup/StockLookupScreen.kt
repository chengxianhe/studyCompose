package com.study.cc.feature.stocklookup

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.study.cc.core.designsystem.component.AppTextField
import com.study.cc.core.designsystem.theme.Spacing

@Composable
fun StockLookupRoute(modifier: Modifier = Modifier, viewModel: StockLookupViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    StockLookupScreen(
        uiState = uiState,
        onInputChange = viewModel::onInputChange,
        onSubmitClick = viewModel::onSubmitClick,
        modifier = modifier,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StockLookupScreen(
    uiState: StockLookupUiState,
    onInputChange: (String) -> Unit,
    onSubmitClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Scaffold(
        modifier = modifier,
        topBar = { TopAppBar(title = { Text(text = stringResource(R.string.stocklookup_title)) }) },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .padding(innerPadding)
                .padding(Spacing.lg),
            verticalArrangement = Arrangement.spacedBy(Spacing.md),
        ) {
            AppTextField(
                value = uiState.input,
                onValueChange = onInputChange,
                label = stringResource(R.string.stocklookup_code_label),
                errorMessage = uiState.error?.let { stringResource(it.messageRes()) },
                modifier = Modifier.fillMaxWidth(),
            )
            Button(onClick = onSubmitClick) {
                Text(text = stringResource(R.string.stocklookup_submit_action))
            }
            uiState.resolved?.let { id ->
                Text(
                    text = stringResource(R.string.stocklookup_resolved_message, "${id.market} ${id.code}"),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
    }
}

private fun StockLookupError.messageRes(): Int = when (this) {
    StockLookupError.Empty -> R.string.stocklookup_error_empty
    StockLookupError.InvalidFormat -> R.string.stocklookup_error_format
    StockLookupError.UnsupportedMarket -> R.string.stocklookup_error_unsupported_market
}
