#include "urma_failure_378.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure378> g_urma("urma_378");

bool UrmaFailure378::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("post_send_check_jfs_wr_valid") != std::string::npos &&
           message.find("when set faa_wr, either src or dst is NULL.") != std::string::npos;
}

std::string UrmaFailure378::GetName() const
{
    return "JFS、工作请求、valid状态不满足要求导致投递JFS、工作请求、valid失败";
}

std::string UrmaFailure378::GetRootCauseDesc() const
{
    return "post_send_check_jfs_wr_"
           "valid执行投递JFS、工作请求、valid时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure378::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure378::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure378::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：post_send_check_jfs_wr_valid，when set faa_wr, either src or dst is "
           "NULL.。";
}

std::string UrmaFailure378::GetId() const
{
    return "urma_378";
}
} // namespace diag
