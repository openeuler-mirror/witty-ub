#include "urma_failure_301.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure301> g_urma("urma_301");

bool UrmaFailure301::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'deepcopy_jfs_wr_node' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Deepcopy sg failed'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure301::GetName() const
{
    return "deepcopy_jfs_wr_node 执行复制 JFS 失败导致当前资源状态无法推进";
}

std::string UrmaFailure301::GetRootCauseDesc() const
{
    return "deepcopy_jfs_wr_node 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure301::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure301::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure301::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Deepcopy sg failed";
}

std::string UrmaFailure301::GetId() const
{
    return "urma_301";
}

} // namespace diag
