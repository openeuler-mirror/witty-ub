#include "urma_failure_216.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure216> g_urma("urma_216");

bool UrmaFailure216::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_segment_uninit_comp_attr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'invalid param'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure216::GetName() const
{
    return "bondp_segment_uninit_comp_attr 校验 segment 无效导致初始化流程拒绝继续执行";
}

std::string UrmaFailure216::GetRootCauseDesc() const
{
    return "bondp_segment_uninit_comp_attr 在执行初始化前发现调用方传入的 segment "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure216::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure216::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure216::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：invalid param";
}

std::string UrmaFailure216::GetId() const
{
    return "urma_216";
}

} // namespace diag
