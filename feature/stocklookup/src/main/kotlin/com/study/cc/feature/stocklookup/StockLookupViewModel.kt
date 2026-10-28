package com.study.cc.feature.stocklookup

import androidx.lifecycle.ViewModel
import com.study.cc.domain.usecase.StockCodeValidation
import com.study.cc.domain.usecase.ValidateStockCodeUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import javax.inject.Inject

@HiltViewModel
class StockLookupViewModel
@Inject
constructor(private val validateStockCode: ValidateStockCodeUseCase) : ViewModel() {
    private val _uiState = MutableStateFlow(StockLookupUiState())
    val uiState: StateFlow<StockLookupUiState> = _uiState.asStateFlow()

    // 输入过程中不打扰用户：空输入不报错，只有点确认时才提示
    fun onInputChange(input: String) {
        val error = validateStockCode(input).toError()?.takeUnless { it == StockLookupError.Empty }
        _uiState.update { StockLookupUiState(input = input, error = error) }
    }

    fun onSubmitClick() {
        val validation = validateStockCode(_uiState.value.input)
        _uiState.update {
            it.copy(
                error = validation.toError(),
                resolved = (validation as? StockCodeValidation.Valid)?.securityId,
            )
        }
    }
}

private fun StockCodeValidation.toError(): StockLookupError? = when (this) {
    is StockCodeValidation.Valid -> null
    StockCodeValidation.Empty -> StockLookupError.Empty
    StockCodeValidation.InvalidFormat -> StockLookupError.InvalidFormat
    StockCodeValidation.UnsupportedMarket -> StockLookupError.UnsupportedMarket
}
