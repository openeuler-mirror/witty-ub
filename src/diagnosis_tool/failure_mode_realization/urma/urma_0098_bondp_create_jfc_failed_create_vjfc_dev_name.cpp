#include "urma_0098_bondp_create_jfc_failed_create_vjfc_dev_name.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0098BondpCreateJfcFailedCreateVjfcDevName> g_urma("urma_0098");

bool Urma0098BondpCreateJfcFailedCreateVjfcDevName::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create vjfc, dev_name: %, eid_idx: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0098BondpCreateJfcFailedCreateVjfcDevName::GetName() const
{
    return "bondp_create_jfc Failed to create vjfc, dev_name: %,";
}

std::string Urma0098BondpCreateJfcFailedCreateVjfcDevName::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0098BondpCreateJfcFailedCreateVjfcDevName::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0098BondpCreateJfcFailedCreateVjfcDevName::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0098BondpCreateJfcFailedCreateVjfcDevName::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create vjfc, dev_name: %, eid_idx: %.";
}

std::string Urma0098BondpCreateJfcFailedCreateVjfcDevName::GetId() const
{
    return "urma_0098";
}
} // namespace diag
