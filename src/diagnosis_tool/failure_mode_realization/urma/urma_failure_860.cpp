#include "urma_failure_860.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure860> g_urma("urma_860");

bool UrmaFailure860::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bdp_slide_wnd_add' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid param wnd'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure860::GetName() const
{
    return "bdp_slide_wnd_add 校验 URMA 对象 无效导致处理流程拒绝继续执行";
}

std::string UrmaFailure860::GetRootCauseDesc() const
{
    return "bdp_slide_wnd_add 在执行处理前发现调用方传入的 URMA 对象 "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure860::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure860::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure860::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid param wnd";
}

std::string UrmaFailure860::GetId() const
{
    return "urma_860";
}

} // namespace diag
