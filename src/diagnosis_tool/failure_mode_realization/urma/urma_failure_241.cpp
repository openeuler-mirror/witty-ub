#include "urma_failure_241.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure241> g_urma("urma_241");

bool UrmaFailure241::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'set_jfs_wr_ptseg_ptjetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Unsupported send opcode'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure241::GetName() const
{
    return "set_jfs_wr_ptseg_ptjetty 执行设置 目标 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure241::GetRootCauseDesc() const
{
    return "set_jfs_wr_ptseg_ptjetty 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure241::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure241::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure241::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Unsupported send opcode";
}

std::string UrmaFailure241::GetId() const
{
    return "urma_241";
}

} // namespace diag
