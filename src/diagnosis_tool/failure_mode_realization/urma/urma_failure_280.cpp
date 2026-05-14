#include "urma_failure_280.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure280> g_urma("urma_280");

bool UrmaFailure280::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bdp_slide_wnd_init' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid param wnd')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure280::GetName() const
{
    return "bdp_slide_wnd_init 校验 URMA 对象 无效导致初始化流程拒绝继续执行";
}

std::string UrmaFailure280::GetRootCauseDesc() const
{
    return "bdp_slide_wnd_init 在执行初始化前发现调用方传入的 URMA 对象 "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure280::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure280::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure280::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid param wnd";
}

std::string UrmaFailure280::GetId() const
{
    return "urma_280";
}

} // namespace diag
