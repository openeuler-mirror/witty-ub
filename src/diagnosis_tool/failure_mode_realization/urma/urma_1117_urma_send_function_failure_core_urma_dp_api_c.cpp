#include "urma_1117_urma_send_function_failure_core_urma_dp_api_c.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1117UrmaSendFunctionFailureCoreUrmaDpApiC> g_urma("urma_1117");

bool Urma1117UrmaSendFunctionFailureCoreUrmaDpApiC::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1118", "urma_1119"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1117UrmaSendFunctionFailureCoreUrmaDpApiC::GetName() const
{
    return "urma_send 函数故障（core/urma_dp_api.c）";
}

std::string Urma1117UrmaSendFunctionFailureCoreUrmaDpApiC::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1117UrmaSendFunctionFailureCoreUrmaDpApiC::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1117UrmaSendFunctionFailureCoreUrmaDpApiC::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1117UrmaSendFunctionFailureCoreUrmaDpApiC::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1117UrmaSendFunctionFailureCoreUrmaDpApiC::GetId() const
{
    return "urma_1117";
}
} // namespace diag
