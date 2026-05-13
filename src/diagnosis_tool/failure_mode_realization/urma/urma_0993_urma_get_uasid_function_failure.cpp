#include "urma_0993_urma_get_uasid_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0993UrmaGetUasidFunctionFailure> g_urma("urma_0993");

bool Urma0993UrmaGetUasidFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0994"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0993UrmaGetUasidFunctionFailure::GetName() const
{
    return "urma_get_uasid 函数故障";
}

std::string Urma0993UrmaGetUasidFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0993UrmaGetUasidFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0993UrmaGetUasidFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0993UrmaGetUasidFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0993UrmaGetUasidFunctionFailure::GetId() const
{
    return "urma_0993";
}
} // namespace diag
