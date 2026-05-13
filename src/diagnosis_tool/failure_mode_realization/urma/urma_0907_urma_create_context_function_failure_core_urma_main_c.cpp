#include "urma_0907_urma_create_context_function_failure_core_urma_main_c.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0907UrmaCreateContextFunctionFailureCoreUrmaMainC> g_urma("urma_0907");

bool Urma0907UrmaCreateContextFunctionFailureCoreUrmaMainC::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0908"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0907UrmaCreateContextFunctionFailureCoreUrmaMainC::GetName() const
{
    return "urma_create_context 函数故障（core/urma_main.c）";
}

std::string Urma0907UrmaCreateContextFunctionFailureCoreUrmaMainC::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0907UrmaCreateContextFunctionFailureCoreUrmaMainC::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0907UrmaCreateContextFunctionFailureCoreUrmaMainC::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0907UrmaCreateContextFunctionFailureCoreUrmaMainC::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0907UrmaCreateContextFunctionFailureCoreUrmaMainC::GetId() const
{
    return "urma_0907";
}
} // namespace diag
