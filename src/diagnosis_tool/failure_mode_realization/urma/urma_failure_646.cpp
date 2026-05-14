#include "urma_failure_646.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure646> g_urma("urma_646");

bool UrmaFailure646::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_post_send_wr_no_store' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'WR->tjetty is NULL')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure646::GetName() const
{
    return "bondp_post_send_wr_no_store 执行投递 目标 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure646::GetRootCauseDesc() const
{
    return "bondp_post_send_wr_no_store 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure646::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure646::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure646::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：WR->tjetty is NULL";
}

std::string UrmaFailure646::GetId() const
{
    return "urma_646";
}

} // namespace diag
