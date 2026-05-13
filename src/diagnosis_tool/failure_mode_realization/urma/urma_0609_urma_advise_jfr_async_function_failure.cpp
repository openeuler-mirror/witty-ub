#include "urma_0609_urma_advise_jfr_async_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0609UrmaAdviseJfrAsyncFunctionFailure> g_urma("urma_0609");

bool Urma0609UrmaAdviseJfrAsyncFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0610", "urma_0611"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0609UrmaAdviseJfrAsyncFunctionFailure::GetName() const
{
    return "urma_advise_jfr_async 函数故障";
}

std::string Urma0609UrmaAdviseJfrAsyncFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0609UrmaAdviseJfrAsyncFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0609UrmaAdviseJfrAsyncFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0609UrmaAdviseJfrAsyncFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0609UrmaAdviseJfrAsyncFunctionFailure::GetId() const
{
    return "urma_0609";
}
} // namespace diag
