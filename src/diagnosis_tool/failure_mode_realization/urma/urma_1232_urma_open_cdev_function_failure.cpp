#include "urma_1232_urma_open_cdev_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1232UrmaOpenCdevFunctionFailure> g_urma("urma_1232");

bool Urma1232UrmaOpenCdevFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1233"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1232UrmaOpenCdevFunctionFailure::GetName() const
{
    return "urma_open_cdev 函数故障";
}

std::string Urma1232UrmaOpenCdevFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1232UrmaOpenCdevFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1232UrmaOpenCdevFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1232UrmaOpenCdevFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1232UrmaOpenCdevFunctionFailure::GetId() const
{
    return "urma_1232";
}
} // namespace diag
