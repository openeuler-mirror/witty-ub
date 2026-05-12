#include "urma_0919_get_dev_ctx_eid_create_context_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0919GetDevCtxEidCreateContextFailure> g_urma("urma_0919");

bool Urma0919GetDevCtxEidCreateContextFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create context"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0919GetDevCtxEidCreateContextFailure::GetName() const
{
    return "get_dev_and_ctx_by_eid 创建context失败";
}

std::string Urma0919GetDevCtxEidCreateContextFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma0919GetDevCtxEidCreateContextFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0919GetDevCtxEidCreateContextFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0919GetDevCtxEidCreateContextFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create context";
}

std::string Urma0919GetDevCtxEidCreateContextFailure::GetId() const
{
    return "urma_0919";
}
} // namespace diag
