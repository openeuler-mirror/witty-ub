#include "urma_failure_223.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure223> g_urma("urma_223");

bool UrmaFailure223::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'set_write_wr_ptseg_ptjetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'tjetty in WR is NULL'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure223::GetName() const
{
    return "set_write_wr_ptseg_ptjetty 执行设置 目标 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure223::GetRootCauseDesc() const
{
    return "set_write_wr_ptseg_ptjetty 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure223::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure223::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure223::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：tjetty in WR is NULL";
}

std::string UrmaFailure223::GetId() const
{
    return "urma_223";
}

} // namespace diag
