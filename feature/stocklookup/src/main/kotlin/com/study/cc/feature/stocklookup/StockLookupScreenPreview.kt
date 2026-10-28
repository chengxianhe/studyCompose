package com.study.cc.feature.stocklookup

import androidx.compose.runtime.Composable
import androidx.compose.ui.tooling.preview.Preview
import com.study.cc.core.designsystem.theme.AppTheme
import com.study.cc.domain.model.Market
import com.study.cc.domain.model.SecurityId

@Preview(showBackground = true)
@Composable
internal fun StockLookupScreenErrorPreview() {
    AppTheme {
        StockLookupScreen(
            uiState = StockLookupUiState(input = "60001", error = StockLookupError.InvalidFormat),
            onInputChange = {},
            onSubmitClick = {},
        )
    }
}

@Preview(showBackground = true)
@Composable
internal fun StockLookupScreenResolvedPreview() {
    AppTheme {
        StockLookupScreen(
            uiState = StockLookupUiState(input = "600001", resolved = SecurityId(Market.SSE, "600001")),
            onInputChange = {},
            onSubmitClick = {},
        )
    }
}
