package com.study.cc.feature.stocklookup

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.Market
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.usecase.ResolveSecurityIdUseCase
import com.study.cc.domain.usecase.ValidateStockCodeUseCase
import org.junit.Test

class StockLookupViewModelTest {
    private val viewModel = StockLookupViewModel(ValidateStockCodeUseCase(ResolveSecurityIdUseCase()))

    @Test
    fun typingDoesNotShowEmptyError() {
        viewModel.onInputChange("")

        assertThat(viewModel.uiState.value.error).isNull()
    }

    @Test
    fun typingShowsFormatErrorImmediately() {
        viewModel.onInputChange("60A")

        assertThat(viewModel.uiState.value.error).isEqualTo(StockLookupError.InvalidFormat)
    }

    @Test
    fun submitEmptyShowsEmptyError() {
        viewModel.onSubmitClick()

        assertThat(viewModel.uiState.value.error).isEqualTo(StockLookupError.Empty)
        assertThat(viewModel.uiState.value.resolved).isNull()
    }

    @Test
    fun submitUnsupportedMarketShowsError() {
        viewModel.onInputChange("900001")
        viewModel.onSubmitClick()

        assertThat(viewModel.uiState.value.error).isEqualTo(StockLookupError.UnsupportedMarket)
    }

    @Test
    fun submitValidCodeResolvesAndEditingClearsResult() {
        viewModel.onInputChange("600001")
        viewModel.onSubmitClick()

        assertThat(viewModel.uiState.value.resolved).isEqualTo(SecurityId(Market.SSE, "600001"))
        assertThat(viewModel.uiState.value.error).isNull()

        viewModel.onInputChange("60000")

        assertThat(viewModel.uiState.value.resolved).isNull()
    }
}
