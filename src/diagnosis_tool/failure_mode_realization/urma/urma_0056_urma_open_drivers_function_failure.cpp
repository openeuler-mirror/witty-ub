#include "urma_0056_urma_open_drivers_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0056UrmaOpenDriversFunctionFailure> g_urma("urma_0056");

bool Urma0056UrmaOpenDriversFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0057", "urma_0058", "urma_0059",
                                                    "urma_0060", "urma_0061", "urma_0062"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0056UrmaOpenDriversFunctionFailure::GetName() const
{
    return "urma_open_drivers 函数故障";
}

std::string Urma0056UrmaOpenDriversFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0056UrmaOpenDriversFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0056UrmaOpenDriversFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0056UrmaOpenDriversFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0056UrmaOpenDriversFunctionFailure::GetId() const
{
    return "urma_0056";
}
} // namespace diag
