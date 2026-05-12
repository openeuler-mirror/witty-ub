#include "urma_0337_delete_copied_jfr_wr_node_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0337DeleteCopiedJfrWrNodeResourceDeleteFailure> g_urma("urma_0337");

bool Urma0337DeleteCopiedJfrWrNodeResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid jfr wr to delete"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0337DeleteCopiedJfrWrNodeResourceDeleteFailure::GetName() const
{
    return "delete_copied_jfr_wr_node 删除资源失败";
}

std::string Urma0337DeleteCopiedJfrWrNodeResourceDeleteFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0337DeleteCopiedJfrWrNodeResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0337DeleteCopiedJfrWrNodeResourceDeleteFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0337DeleteCopiedJfrWrNodeResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid jfr wr to delete";
}

std::string Urma0337DeleteCopiedJfrWrNodeResourceDeleteFailure::GetId() const
{
    return "urma_0337";
}
} // namespace diag
