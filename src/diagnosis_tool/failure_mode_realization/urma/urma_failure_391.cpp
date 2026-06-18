#include "urma_failure_391.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure391> g_urma("urma_391");

bool UrmaFailure391::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("post_recv_check_wr_list_valid") != std::string::npos &&
           message.find("Invalid bdp_recv_comp type:") != std::string::npos;
}

std::string UrmaFailure391::GetName() const
{
    return "工作请求、列表、valid状态不满足要求导致投递工作请求、列表、valid失败";
}

std::string UrmaFailure391::GetRootCauseDesc() const
{
    return "post_recv_check_wr_list_"
           "valid执行投递工作请求、列表、valid时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure391::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure391::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure391::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：post_recv_check_wr_list_valid，Invalid bdp_recv_comp type:。";
}

std::string UrmaFailure391::GetId() const
{
    return "urma_391";
}
} // namespace diag
