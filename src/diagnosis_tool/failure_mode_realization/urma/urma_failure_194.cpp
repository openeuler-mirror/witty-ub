#include "urma_failure_194.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure194> g_urma("urma_194");

bool UrmaFailure194::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_create_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'In matrix server, jetty only supports single-path mode with RC'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure194::GetName() const
{
    return "bondp_create_jetty 校验 Jetty 业务条件不满足导致创建流程拒绝继续执行";
}

std::string UrmaFailure194::GetRootCauseDesc() const
{
    return "bondp_create_jetty 在执行创建时发现 Jetty "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure194::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure194::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure194::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：In matrix server, jetty only supports single-path mode with RC";
}

std::string UrmaFailure194::GetId() const
{
    return "urma_194";
}

} // namespace diag
