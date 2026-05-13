#include "urma_0335_delete_copied_jfr_wr_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0335DeleteCopiedJfrWrResourceDeleteFailure> g_urma("urma_0335");

bool Urma0335DeleteCopiedJfrWrResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid jfr wr to delete"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0335DeleteCopiedJfrWrResourceDeleteFailure::GetName() const
{
    return "delete_copied_jfr_wr 删除资源失败";
}

std::string Urma0335DeleteCopiedJfrWrResourceDeleteFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma0335DeleteCopiedJfrWrResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0335DeleteCopiedJfrWrResourceDeleteFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0335DeleteCopiedJfrWrResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid jfr wr to delete";
}

std::string Urma0335DeleteCopiedJfrWrResourceDeleteFailure::GetId() const
{
    return "urma_0335";
}
} // namespace diag
