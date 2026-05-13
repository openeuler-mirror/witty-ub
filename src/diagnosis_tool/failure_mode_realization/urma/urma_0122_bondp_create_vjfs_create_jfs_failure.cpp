#include "urma_0122_bondp_create_vjfs_create_jfs_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0122BondpCreateVjfsCreateJfsFailure> g_urma("urma_0122");

bool Urma0122BondpCreateVjfsCreateJfsFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ubcore create jfs failed."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0122BondpCreateVjfsCreateJfsFailure::GetName() const
{
    return "bondp_create_vjfs 创建JFS失败";
}

std::string Urma0122BondpCreateVjfsCreateJfsFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma0122BondpCreateVjfsCreateJfsFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0122BondpCreateVjfsCreateJfsFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0122BondpCreateVjfsCreateJfsFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ubcore create jfs failed.";
}

std::string Urma0122BondpCreateVjfsCreateJfsFailure::GetId() const
{
    return "urma_0122";
}
} // namespace diag
