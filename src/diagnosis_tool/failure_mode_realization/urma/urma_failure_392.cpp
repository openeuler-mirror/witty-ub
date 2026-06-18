#include "urma_failure_392.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure392> g_urma("urma_392");

bool UrmaFailure392::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("handle_send_cr_with_store") != std::string::npos &&
           message.find("Failed find jetty when handle send cr, cr.local_id:") != std::string::npos;
}

std::string UrmaFailure392::GetName() const
{
    return "发送handle、CR、WITH执行失败导致发送handle、CR、WITH失败";
}

std::string UrmaFailure392::GetRootCauseDesc() const
{
    return "handle_send_cr_with_"
           "store执行发送handle、CR、WITH时依赖的发送handle、CR、WITH步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure392::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure392::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure392::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：handle_send_cr_with_store，Failed find jetty when handle send cr, "
           "cr.local_id:"
           "。";
}

std::string UrmaFailure392::GetId() const
{
    return "urma_392";
}
} // namespace diag
