#include "urma_0884_urma_send_function_failure_core_urma_dp_api_c.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0884UrmaSendFunctionFailureCoreUrmaDpApiC> g_urma("urma_0884");

bool Urma0884UrmaSendFunctionFailureCoreUrmaDpApiC::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0885"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0884UrmaSendFunctionFailureCoreUrmaDpApiC::GetName() const
{
    return "urma_send 函数故障（core/urma_dp_api.c）";
}

std::string Urma0884UrmaSendFunctionFailureCoreUrmaDpApiC::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0884UrmaSendFunctionFailureCoreUrmaDpApiC::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0884UrmaSendFunctionFailureCoreUrmaDpApiC::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0884UrmaSendFunctionFailureCoreUrmaDpApiC::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0884UrmaSendFunctionFailureCoreUrmaDpApiC::GetId() const
{
    return "urma_0884";
}
} // namespace diag
