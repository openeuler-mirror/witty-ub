#include "urma_failure_569.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure569> g_urma("urma_569");

bool UrmaFailure569::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_unimport_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid bdp tjetty'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure569::GetName() const
{
    return "bondp_unimport_jfr 校验 目标 Jetty 无效导致导入流程拒绝继续执行";
}

std::string UrmaFailure569::GetRootCauseDesc() const
{
    return "bondp_unimport_jfr 在执行导入前发现调用方传入的 目标 Jetty "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure569::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure569::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure569::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid bdp tjetty";
}

std::string UrmaFailure569::GetId() const
{
    return "urma_569";
}

} // namespace diag
