#include "urma_failure_495.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure495> g_urma("urma_495");

bool UrmaFailure495::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'get_comp_urma_jetty_id' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to get_comp_urma_jetty, Invalid type')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure495::GetName() const
{
    return "get_comp_urma_jetty_id 校验 Jetty 无效导致获取流程拒绝继续执行";
}

std::string UrmaFailure495::GetRootCauseDesc() const
{
    return "get_comp_urma_jetty_id 在执行获取前发现调用方传入的 Jetty "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure495::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure495::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure495::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to get_comp_urma_jetty, Invalid type";
}

std::string UrmaFailure495::GetId() const
{
    return "urma_495";
}

} // namespace diag
