#include "urma_failure_858.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure858> g_urma("urma_858");

bool UrmaFailure858::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bdp_slide_wnd_has' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid param wnd')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure858::GetName() const
{
    return "bdp_slide_wnd_has 校验 URMA 对象 无效导致处理流程拒绝继续执行";
}

std::string UrmaFailure858::GetRootCauseDesc() const
{
    return "bdp_slide_wnd_has 在执行处理前发现调用方传入的 URMA 对象 "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure858::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure858::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure858::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid param wnd";
}

std::string UrmaFailure858::GetId() const
{
    return "urma_858";
}

} // namespace diag
