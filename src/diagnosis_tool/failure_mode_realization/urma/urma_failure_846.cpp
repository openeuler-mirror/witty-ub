#include "urma_failure_846.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure846> g_urma("urma_846");

bool UrmaFailure846::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'add_remote_jetty_id_info' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to add bdp_r_p2v_vjetty_id[]: ret: , jetty_id')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure846::GetName() const
{
    return "add_remote_jetty_id_info 执行处理 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure846::GetRootCauseDesc() const
{
    return "add_remote_jetty_id_info 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure846::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure846::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure846::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to add bdp_r_p2v_vjetty_id[]: ret: , jetty_id";
}

std::string UrmaFailure846::GetId() const
{
    return "urma_846";
}

} // namespace diag
