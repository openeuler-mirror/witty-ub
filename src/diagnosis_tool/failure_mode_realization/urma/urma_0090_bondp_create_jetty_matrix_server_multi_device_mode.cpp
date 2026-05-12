#include "urma_0090_bondp_create_jetty_matrix_server_multi_device_mode.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0090BondpCreateJettyMatrixServerMultiDeviceMode> g_urma("urma_0090");

bool Urma0090BondpCreateJettyMatrixServerMultiDeviceMode::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "In matrix server, multi-device mode don't support single path currently."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0090BondpCreateJettyMatrixServerMultiDeviceMode::GetName() const
{
    return "bondp_create_jetty In matrix server, multi-device mode";
}

std::string Urma0090BondpCreateJettyMatrixServerMultiDeviceMode::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_single_dev_mode(ctx)`；该路径返回 NULL";
}

RootCause Urma0090BondpCreateJettyMatrixServerMultiDeviceMode::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0090BondpCreateJettyMatrixServerMultiDeviceMode::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0090BondpCreateJettyMatrixServerMultiDeviceMode::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：In matrix server, multi-device mode don't support single path "
           "currently.";
}

std::string Urma0090BondpCreateJettyMatrixServerMultiDeviceMode::GetId() const
{
    return "urma_0090";
}
} // namespace diag
