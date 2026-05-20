#include "urma_failure_211.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure211> g_urma("urma_211");

bool UrmaFailure211::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_jfr_get_args_list' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid param jfc'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure211::GetName() const
{
    return "bondp_jfr_get_args_list 校验 JFR 无效导致获取流程拒绝继续执行";
}

std::string UrmaFailure211::GetRootCauseDesc() const
{
    return "bondp_jfr_get_args_list 在执行获取前发现调用方传入的 JFR "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure211::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure211::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure211::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid param jfc";
}

std::string UrmaFailure211::GetId() const
{
    return "urma_211";
}

} // namespace diag
