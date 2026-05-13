#include "urma_0905_urma_log_set_thread_tag_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0905UrmaLogSetThreadTagFunctionFailure> g_urma("urma_0905");

bool Urma0905UrmaLogSetThreadTagFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0906"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0905UrmaLogSetThreadTagFunctionFailure::GetName() const
{
    return "urma_log_set_thread_tag 函数故障";
}

std::string Urma0905UrmaLogSetThreadTagFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0905UrmaLogSetThreadTagFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0905UrmaLogSetThreadTagFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0905UrmaLogSetThreadTagFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0905UrmaLogSetThreadTagFunctionFailure::GetId() const
{
    return "urma_0905";
}
} // namespace diag
