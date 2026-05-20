#include "urma_failure_870.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure870> g_urma("urma_870");

bool UrmaFailure870::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'deepcopy_jfs_wr_inner' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to copy in wr->next'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure870::GetName() const
{
    return "deepcopy_jfs_wr_inner 执行复制 JFS 失败导致当前资源状态无法推进";
}

std::string UrmaFailure870::GetRootCauseDesc() const
{
    return "deepcopy_jfs_wr_inner 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure870::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure870::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure870::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to copy in wr->next";
}

std::string UrmaFailure870::GetId() const
{
    return "urma_870";
}

} // namespace diag
