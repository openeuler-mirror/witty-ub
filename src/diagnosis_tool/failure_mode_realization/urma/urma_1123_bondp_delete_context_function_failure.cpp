#include "urma_1123_bondp_delete_context_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1123BondpDeleteContextFunctionFailure> g_urma("urma_1123");

bool Urma1123BondpDeleteContextFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1124", "urma_1125"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1123BondpDeleteContextFunctionFailure::GetName() const
{
    return "bondp_delete_context 函数故障";
}

std::string Urma1123BondpDeleteContextFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1123BondpDeleteContextFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1123BondpDeleteContextFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1123BondpDeleteContextFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1123BondpDeleteContextFunctionFailure::GetId() const
{
    return "urma_1123";
}
} // namespace diag
