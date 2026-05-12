#include "urma_1174_urma_create_context_function_failure_core_urma_main_c.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1174UrmaCreateContextFunctionFailureCoreUrmaMainC> g_urma("urma_1174");

bool Urma1174UrmaCreateContextFunctionFailureCoreUrmaMainC::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1175", "urma_1176"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1174UrmaCreateContextFunctionFailureCoreUrmaMainC::GetName() const
{
    return "urma_create_context 函数故障（core/urma_main.c）";
}

std::string Urma1174UrmaCreateContextFunctionFailureCoreUrmaMainC::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1174UrmaCreateContextFunctionFailureCoreUrmaMainC::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1174UrmaCreateContextFunctionFailureCoreUrmaMainC::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1174UrmaCreateContextFunctionFailureCoreUrmaMainC::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1174UrmaCreateContextFunctionFailureCoreUrmaMainC::GetId() const
{
    return "urma_1174";
}
} // namespace diag
