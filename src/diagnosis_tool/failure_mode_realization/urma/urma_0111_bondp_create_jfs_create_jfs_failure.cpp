#include "urma_0111_bondp_create_jfs_create_jfs_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0111BondpCreateJfsCreateJfsFailure> g_urma("urma_0111");

bool Urma0111BondpCreateJfsCreateJfsFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create jfs datapath ctx"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0111BondpCreateJfsCreateJfsFailure::GetName() const
{
    return "bondp_create_jfs 创建JFS失败";
}

std::string Urma0111BondpCreateJfsCreateJfsFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0111BondpCreateJfsCreateJfsFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0111BondpCreateJfsCreateJfsFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0111BondpCreateJfsCreateJfsFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create jfs datapath ctx";
}

std::string Urma0111BondpCreateJfsCreateJfsFailure::GetId() const
{
    return "urma_0111";
}
} // namespace diag
