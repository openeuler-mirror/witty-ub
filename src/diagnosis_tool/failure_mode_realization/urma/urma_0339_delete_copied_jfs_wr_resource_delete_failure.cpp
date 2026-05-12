#include "urma_0339_delete_copied_jfs_wr_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0339DeleteCopiedJfsWrResourceDeleteFailure> g_urma("urma_0339");

bool Urma0339DeleteCopiedJfsWrResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid jfs wr to delete"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0339DeleteCopiedJfsWrResourceDeleteFailure::GetName() const
{
    return "delete_copied_jfs_wr 删除资源失败";
}

std::string Urma0339DeleteCopiedJfsWrResourceDeleteFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma0339DeleteCopiedJfsWrResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0339DeleteCopiedJfsWrResourceDeleteFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0339DeleteCopiedJfsWrResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid jfs wr to delete";
}

std::string Urma0339DeleteCopiedJfsWrResourceDeleteFailure::GetId() const
{
    return "urma_0339";
}
} // namespace diag
