#include "urma_failure_237.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure237> g_urma("urma_237");

bool UrmaFailure237::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'set_fadd_wr_ptseg_pjetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid vtjetty, the structure may be self-consturcted'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure237::GetName() const
{
    return "set_fadd_wr_ptseg_pjetty 校验 目标 Jetty 无效导致设置流程拒绝继续执行";
}

std::string UrmaFailure237::GetRootCauseDesc() const
{
    return "set_fadd_wr_ptseg_pjetty 在执行设置前发现调用方传入的 目标 Jetty "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure237::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure237::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure237::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid vtjetty, the structure may be self-consturcted";
}

std::string UrmaFailure237::GetId() const
{
    return "urma_237";
}

} // namespace diag
