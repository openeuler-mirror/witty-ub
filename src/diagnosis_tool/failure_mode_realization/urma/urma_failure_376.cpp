#include "urma_failure_376.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure376> g_urma("urma_376");

bool UrmaFailure376::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("post_send_check_jfs_wr_valid") != std::string::npos &&
           message.find("when set write_wr, either of src/dst num_sge/sge has been set zero or NULL.") !=
               std::string::npos;
}

std::string UrmaFailure376::GetName() const
{
    return "JFS、工作请求、valid状态不满足要求导致投递JFS、工作请求、valid失败";
}

std::string UrmaFailure376::GetRootCauseDesc() const
{
    return "post_send_check_jfs_wr_"
           "valid执行投递JFS、工作请求、valid时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure376::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure376::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure376::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：post_send_check_jfs_wr_valid，when set write_wr, either of src/dst "
           "num_sge/sge"
           " has been set zero or NULL.。";
}

std::string UrmaFailure376::GetId() const
{
    return "urma_376";
}
} // namespace diag
