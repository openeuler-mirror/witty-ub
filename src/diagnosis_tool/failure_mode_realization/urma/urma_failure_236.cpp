#include "urma_failure_236.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure236> g_urma("urma_236");

bool UrmaFailure236::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'set_fadd_wr_ptseg_pjetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'tjetty in WR is NULL'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure236::GetName() const
{
    return "set_fadd_wr_ptseg_pjetty 执行设置 目标 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure236::GetRootCauseDesc() const
{
    return "set_fadd_wr_ptseg_pjetty 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure236::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure236::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure236::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：tjetty in WR is NULL";
}

std::string UrmaFailure236::GetId() const
{
    return "urma_236";
}

} // namespace diag
