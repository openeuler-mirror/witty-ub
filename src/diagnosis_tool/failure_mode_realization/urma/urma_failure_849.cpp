#include "urma_failure_849.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure849> g_urma("urma_849");

bool UrmaFailure849::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'encode_jfs_wr_reliable_info' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Unsupported send opcode')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure849::GetName() const
{
    return "encode_jfs_wr_reliable_info 执行处理 JFS 失败导致当前资源状态无法推进";
}

std::string UrmaFailure849::GetRootCauseDesc() const
{
    return "encode_jfs_wr_reliable_info 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure849::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure849::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure849::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Unsupported send opcode";
}

std::string UrmaFailure849::GetId() const
{
    return "urma_849";
}

} // namespace diag
