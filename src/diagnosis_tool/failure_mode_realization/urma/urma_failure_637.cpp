#include "urma_failure_637.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure637> g_urma("urma_637");

bool UrmaFailure637::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'post_send_check_jfs_wr_valid' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'when set faa_wr, either src or dst is NULL')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure637::GetName() const
{
    return "post_send_check_jfs_wr_valid 执行投递 JFS 失败导致当前资源状态无法推进";
}

std::string UrmaFailure637::GetRootCauseDesc() const
{
    return "post_send_check_jfs_wr_valid 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure637::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure637::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure637::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：when set faa_wr, either src or dst is NULL";
}

std::string UrmaFailure637::GetId() const
{
    return "urma_637";
}

} // namespace diag
