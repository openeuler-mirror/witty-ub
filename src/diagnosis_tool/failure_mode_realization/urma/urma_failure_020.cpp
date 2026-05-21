#include "urma_failure_020.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure020> g_urma("urma_020");

bool UrmaFailure020::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_bind_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'The is_multipath attributes of jetty and tjetty are different'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure020::GetName() const
{
    return "bondp_bind_jetty 校验 context 业务条件不满足导致绑定流程拒绝继续执行";
}

std::string UrmaFailure020::GetRootCauseDesc() const
{
    return "bondp_bind_jetty 在执行绑定时发现 context "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure020::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure020::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure020::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：The is_multipath attributes of jetty and tjetty are different";
}

std::string UrmaFailure020::GetId() const
{
    return "urma_020";
}

} // namespace diag
