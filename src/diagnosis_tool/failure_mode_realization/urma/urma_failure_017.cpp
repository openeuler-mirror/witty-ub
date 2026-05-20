#include "urma_failure_017.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure017> g_urma("urma_017");

bool UrmaFailure017::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bind_jetty_single_path' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'No valid direct route'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure017::GetName() const
{
    return "bind_jetty_single_path 校验 Jetty 业务条件不满足导致绑定流程拒绝继续执行";
}

std::string UrmaFailure017::GetRootCauseDesc() const
{
    return "bind_jetty_single_path 在执行绑定时发现 Jetty "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure017::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure017::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure017::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：No valid direct route";
}

std::string UrmaFailure017::GetId() const
{
    return "urma_017";
}

} // namespace diag
