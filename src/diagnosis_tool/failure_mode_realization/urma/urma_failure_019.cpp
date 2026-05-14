#include "urma_failure_019.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure019> g_urma("urma_019");

bool UrmaFailure019::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_bind_jetty' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Jetty already has a binded target jetty')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure019::GetName() const
{
    return "bondp_bind_jetty 校验 Jetty 业务条件不满足导致绑定流程拒绝继续执行";
}

std::string UrmaFailure019::GetRootCauseDesc() const
{
    return "bondp_bind_jetty 在执行绑定时发现 Jetty "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure019::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure019::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure019::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Jetty already has a binded target jetty";
}

std::string UrmaFailure019::GetId() const
{
    return "urma_019";
}

} // namespace diag
