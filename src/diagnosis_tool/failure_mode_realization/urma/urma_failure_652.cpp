#include "urma_failure_652.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure652> g_urma("urma_652");

bool UrmaFailure652::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'send_so_from_snd_queue' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'v_conn has NULL target_vjetty in sending SO')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure652::GetName() const
{
    return "send_so_from_snd_queue 执行发送 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure652::GetRootCauseDesc() const
{
    return "send_so_from_snd_queue 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure652::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure652::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure652::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：v_conn has NULL target_vjetty in sending SO";
}

std::string UrmaFailure652::GetId() const
{
    return "urma_652";
}

} // namespace diag
