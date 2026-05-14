#include "urma_failure_709.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure709> g_urma("urma_709");

bool UrmaFailure709::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'remove_remote_jetty_id_info' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to del bdp_r_p2v_vjetty_id[]: ret: , jetty_id')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure709::GetName() const
{
    return "remove_remote_jetty_id_info 执行处理 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure709::GetRootCauseDesc() const
{
    return "remove_remote_jetty_id_info 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure709::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure709::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure709::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to del bdp_r_p2v_vjetty_id[]: ret: , jetty_id";
}

std::string UrmaFailure709::GetId() const
{
    return "urma_709";
}

} // namespace diag
