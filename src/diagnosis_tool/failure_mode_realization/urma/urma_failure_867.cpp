#include "urma_failure_867.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure867> g_urma("urma_867");

bool UrmaFailure867::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'deepcopy_jfs_wr_node' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Deepcopy faa failed')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure867::GetName() const
{
    return "deepcopy_jfs_wr_node 执行复制 JFS 失败导致当前资源状态无法推进";
}

std::string UrmaFailure867::GetRootCauseDesc() const
{
    return "deepcopy_jfs_wr_node 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure867::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure867::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure867::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Deepcopy faa failed";
}

std::string UrmaFailure867::GetId() const
{
    return "urma_867";
}

} // namespace diag
