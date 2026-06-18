#include "urma_failure_495.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure495> g_urma("urma_495");

bool UrmaFailure495::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_post_jfr_wr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure495::GetName() const
{
    return "dp_ops、post_jfs_wr、工作请求、bad_wr无效导致投递JFR、工作请求失败";
}

std::string UrmaFailure495::GetRootCauseDesc() const
{
    return "urma_post_jfr_wr用于投递JFR、工作请求，调用方传入的dp_ops、post_jfs_wr、工作请求、bad_"
           "wr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure495::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure495::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure495::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_post_jfr_wr，Invalid parameter.。";
}

std::string UrmaFailure495::GetId() const
{
    return "urma_495";
}
} // namespace diag
