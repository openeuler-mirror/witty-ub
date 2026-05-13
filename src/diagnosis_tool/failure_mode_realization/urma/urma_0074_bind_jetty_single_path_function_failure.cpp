#include "urma_0074_bind_jetty_single_path_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0074BindJettySinglePathFunctionFailure> g_urma("urma_0074");

bool Urma0074BindJettySinglePathFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0075"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0074BindJettySinglePathFunctionFailure::GetName() const
{
    return "bind_jetty_single_path 函数故障";
}

std::string Urma0074BindJettySinglePathFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0074BindJettySinglePathFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0074BindJettySinglePathFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0074BindJettySinglePathFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0074BindJettySinglePathFunctionFailure::GetId() const
{
    return "urma_0074";
}
} // namespace diag
