#include "urma_failure_628.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure628> g_urma("urma_628");

bool UrmaFailure628::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'schedule_next_route_in_matrix_server_singlepath' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid single path port. Single path mode only support RC and need to call bind_jetty')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure628::GetName() const
{
    return "schedule_next_route_in_matrix_server_singlepath 校验 context 业务条件不满足导致调度流程拒绝继续执行";
}

std::string UrmaFailure628::GetRootCauseDesc() const
{
    return "schedule_next_route_in_matrix_server_singlepath 在执行调度时发现 context "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure628::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure628::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure628::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid single path port. Single path mode only support RC and need to "
           "call bind_jetty";
}

std::string UrmaFailure628::GetId() const
{
    return "urma_628";
}

} // namespace diag
