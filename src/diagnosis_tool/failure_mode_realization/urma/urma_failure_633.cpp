#include "urma_failure_633.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure633> g_urma("urma_633");

bool UrmaFailure633::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'update_send_wr_before_post' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to set_jfs_wr_ptseg_ptjetty')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure633::GetName() const
{
    return "update_send_wr_before_post 执行投递 目标 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure633::GetRootCauseDesc() const
{
    return "update_send_wr_before_post 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure633::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure633::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure633::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to set_jfs_wr_ptseg_ptjetty";
}

std::string UrmaFailure633::GetId() const
{
    return "urma_633";
}

} // namespace diag
