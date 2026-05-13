#include "urma_0194_import_jfr_default_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0194ImportJfrDefaultFunctionFailure> g_urma("urma_0194");

bool Urma0194ImportJfrDefaultFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0195"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0194ImportJfrDefaultFunctionFailure::GetName() const
{
    return "import_jfr_default 函数故障";
}

std::string Urma0194ImportJfrDefaultFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0194ImportJfrDefaultFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0194ImportJfrDefaultFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0194ImportJfrDefaultFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0194ImportJfrDefaultFunctionFailure::GetId() const
{
    return "urma_0194";
}
} // namespace diag
